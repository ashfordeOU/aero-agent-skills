---
name: extended-kalman-filter
description: "Estimate the state of a nonlinear system with an extended Kalman filter: linearize the nonlinear dynamics and measurement model about the current estimate with the state Jacobian F and the measurement Jacobian H, run the predict step x_hat = f(x_hat), P = F P F^T + Q, then the update step with the innovation y = z - h(x_hat), the innovation covariance S = H P H^T + R, the Kalman gain K = P H^T S^-1, and the corrected state and covariance. Produces the predicted and corrected states, the state and innovation covariances, the gain, and the innovation sequence for nonlinear tracking problems. Use when the task is nonlinear state estimation, Jacobian linearization, or extended Kalman filtering for tracking. Trigger: extended kalman filter, jacobian linearization, innovation covariance, kalman gain, nonlinear state estimation, range bearing tracking."
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
  tags: [extended-kalman-filter, jacobian-linearization, nonlinear-state-estimation, innovation-covariance, kalman-gain, predict-update-recursion, range-bearing-tracking, state-covariance]
  version: 0.1.0
  author: AeroSkills
---

# Extended Kalman Filter (gnc-autonomy/estimation-filtering/extended-kalman-filter)

Use when the task is nonlinear state estimation with an extended Kalman
filter: Jacobian linearization of the dynamics and measurement models,
the predict-update recursion, the innovation covariance and Kalman
gain, and the corrected state and covariance for tracking problems.

The EKF is the Jacobian-linearized cousin of the linear Kalman filter
(navigation/kalman-filter-design) and of the alpha-beta tracker
(estimation-filtering/alpha-beta-filter): it keeps the exact
predict-update loop but replaces the linear model matrices with the
Jacobians of the nonlinear models, evaluated at the current estimate
each step. The unscented Kalman filter (estimation-filtering/
unscented-kalman-filter) is the sigma-point alternative that avoids
differentiation entirely.

## Domain quick reference

- State model: x in R^n with mean x and covariance P. The process is
  x_(k+1) = f(x_k) + w_k with dynamics noise w ~ N(0, Q); the
  measurement is z_k = h(x_k) + v_k with sensor noise v ~ N(0, R).
  Both f and h may be nonlinear.
- Linearization: the state Jacobian F = df/dx and the measurement
  Jacobian H = dh/dx are evaluated at the current estimate each step;
  the nonlinear functions are then treated as locally linear about
  that point, which is what makes the standard Kalman recursion
  applicable.
- Predict: x_hat = f(x_hat) and P = F P F^T + Q with F = jacobian_f(f,
  x) evaluated at the pre-predict state.
- Update: innovation y = z - h(x_hat), innovation covariance
  S = H P H^T + R, Kalman gain K = P H^T S^-1, then x_hat = x_hat +
  K y and P = (I - K H) P, with H = jacobian_h(h, x_hat) evaluated at
  the predicted state.
- The innovation y is the measurement residual the filter could not
  explain; its covariance S is the honest uncertainty of that residual
  (model uncertainty H P H^T plus sensor noise R). The gain K weights
  the correction by how much of the innovation is signal versus noise.
- Covariance behavior: P grows in predict (Q adds uncertainty) and
  shrinks in update (a measurement removes uncertainty); a zero
  innovation leaves the state unchanged while the covariance still
  shrinks by K S K^T.
- Nonlinear examples: range/bearing tracking of a target (h involves
  sqrt and atan2 of the position), orbital or ballistic propagation
  (gravity varies with position), aircraft kinematics with attitude
  (rotation matrices in f), and any sensor model with angles, ranges,
  or products of states.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the extended Kalman filter is common estimation-theory
  knowledge (Gelb; Maybeck; Anderson and Moore).

## Workflow

1. Write the model: dynamics f(x), measurement h(x), the dynamics
   noise covariance Q, the sensor noise covariance R, and the initial
   mean x0 and covariance P0.
2. Confirm the models with the numeric Jacobians: jacobian_f(f, x) and
   jacobian_h(h, x) return F and H by central finite differences
   (deterministic, stdlib only).
3. Predict with ekf_predict(x, P, f, Q); the returned dict carries the
   predicted state x, the predicted covariance P = F P F^T + Q, and
   the Jacobian F used.
4. Update with ekf_update(x, P, z, h, R) on the predicted state; the
   returned dict carries the corrected state, corrected covariance,
   innovation y, innovation covariance S, gain K, and Jacobian H.
5. For a measurement batch, keep an EKFFilter instance and call
   step(z) per measurement; the filter holds x, P, and the last
   innovation, S, and K.
6. For a whole run, call run_ekf(zs, x0, P0, f, h, Q, R) to get one
   entry per measurement step.
7. Watch the innovation sequence: it should shrink as the filter
   converges; a persistently large or biased innovation means the
   model, Q, or R is wrong (or the linearization is too crude).
8. Confirm the deterministic checks with the contract test
   scripts/test_extended_kalman_filter.py.

## Jacobian linearization

The EKF makes the Kalman recursion work for nonlinear models by
linearizing about the current estimate. At each step the dynamics are
replaced by the first-order Taylor model f(x) ~ f(x_hat) + F (x -
x_hat) with F = df/dx, and the measurement model by h(x) ~ h(x_hat) +
H (x - x_hat) with H = dh/dx, both evaluated at the latest estimate.
Because F and H are re-evaluated every step, the filter tracks a
moving linearization point instead of one fixed model.

The Jacobians here are computed by central finite differences:
J[i][j] = (f_i(x + eps e_j) - f_i(x - eps e_j)) / (2 eps). For linear
models the numeric Jacobian recovers the model matrix exactly (to
finite-difference precision), so the EKF reproduces the linear Kalman
filter bit for bit; for nonlinear models it is the local tangent of
the model at the estimate.

The predict step propagates the mean through the exact nonlinear f and
the covariance through the linearized F. The update step forms the
innovation from the exact nonlinear h, then corrects with the gain
built from the linearized H. All matrix algebra is list based and
deterministic; the only approximation is the first-order
linearization itself.

## Tuning guidance

- Q and R are the honest uncertainty budgets. Too small a Q makes the
  filter overconfident and slow to react to true motion; too large a
  Q makes it noisy. R should match the actual sensor noise; an R that
  is too small over-trusts the measurement and the corrected
  covariance understates the error.
- The initial covariance P0 encodes how sure you are of x0; a large
  P0 lets the filter pull the state to the first measurements quickly.
- eps (default 1e-6) is the finite-difference step. It is a good
  default for unit-scaled states; rescale it if the states have very
  different magnitudes.
- If the innovation covariance S is singular (for example a zero
  Jacobian with R = 0), ekf_update raises ValueError; raise R or fix
  the measurement model.
- For strongly nonlinear models the first-order linearization can
  diverge where the UKF stays stable; if the innovation stays large or
  the covariance collapses, switch to the unscented filter or
  re-linearize more often (smaller step sizes).

## Pitfalls

- Confusing the EKF with the linear Kalman filter: the EKF needs the
  exact nonlinear f and h callables and re-computes F and H every
  step; using fixed matrices turns it back into a linear filter.
- Linearizing at the wrong point: F belongs at the pre-predict state,
  H at the predicted state. Linearizing H at the old state biases the
  gain.
- Forgetting Q in predict or R in the innovation covariance; the
  covariance then collapses and the filter becomes overconfident.
- Expecting y = 0 after a good measurement; the innovation is a
  random residual, and only its average size over time indicates
  filter health.
- Feeding R = 0 with a measurement whose Jacobian vanishes at the
  linearization point; S becomes singular and the update raises
  ValueError.
- Ignoring the linearization error: the EKF is a first-order
  approximation, and for strongly nonlinear models the sigma-point UKF
  or a particle filter is the safer choice.

## Worked example

Scalar nonlinear system with f(x) = x + 0.1 sin(x) (mildly expansive
drift) and quadratic measurement h(x) = x^2 / 4. Initial x0 = 2.0,
P0 = 1.0, Q = 0.01, R = 0.25:

- F = 1 + 0.1 cos(2) ~ 0.9584 (numeric Jacobian agrees to five
  digits).
- Predict: x_pred = f(2.0) = 2.0909; P_pred = F^2 P0 + Q ~ 0.9285.
- Measurement z = 1.1: h(x_pred) = x_pred^2 / 4 ~ 1.0930, so the
  innovation y = z - h(x_pred) ~ 0.0070.
- H = x_pred / 2 ~ 1.0455, so S = H^2 P_pred + R ~ 1.2649 and
  K = H P_pred / S ~ 0.7675.
- Correction: x_new = x_pred + K y ~ 2.0963 (moved toward the
  measurement), P_new = (1 - K H) P_pred ~ 0.1835 (uncertainty cut by
  the measurement).

Range/bearing tracking of a constant-velocity target x = [px, py, vx,
vy] with true state (10, 5, 2.0, 0.5) m and m/s, dt = 0.1 s, 40 exact
range/bearing measurements, filter started at (9.5, 5.5, 1.8, 0.4)
with P0 = diag(1, 1, 0.5, 0.5), Q = 1e-4 I, R = diag(1e-3, 1e-4):
the run converges to a final position error of about 0.002 m and the
covariance trace drops from 3.0 to about 0.0078.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_extended_kalman_filter.py

The test covers the numeric Jacobians (linear functions recovered to
finite-difference precision), exact agreement of predict and update
with the hand-computed linear Kalman filter for linear models, the
zero-innovation case (state unchanged, covariance reduced), the
singular innovation covariance edge case, convergence of the nonlinear
range/bearing tracking run, the stateful EKFFilter, the batch runner,
and run-to-run determinism.

## Related leaves

- navigation/kalman-filter-design: the linear Kalman filter the EKF
  generalizes (fixed F and H, same recursion).
- estimation-filtering/unscented-kalman-filter: sigma-point alternative
  for strongly nonlinear models, no Jacobians.
- estimation-filtering/alpha-beta-filter: fixed-gain tracker for
  lightly nonlinear or nearly constant-velocity problems.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
